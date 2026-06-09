#include "ns3/antenna-module.h"
#include "ns3/applications-module.h"
#include "ns3/buildings-module.h"
#include "ns3/config-store-module.h"
#include "ns3/core-module.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/internet-apps-module.h"
#include "ns3/internet-module.h"
#include "ns3/mobility-module.h"
#include "ns3/nr-module.h"
#include "ns3/point-to-point-module.h"

#include <iomanip>
#include <sstream>
#include <algorithm>   
#include <vector>      
#include <chrono>         

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("NrNetworkSlicingExperiment");

/**
 * @brief 网络切片实验主程序
 *
 * 实验设计：
 * - 对照组（Control）：所有UE使用相同优先级或RR调度器，无切片区分
 * - 实验组（Treatment）：启用切片，uRLLC配置GBR+高优先级，eMBB配置NGBR+低优先级
 *
 * 关键配置：
 * 1. 调度器类型：TdmaRR（对照） vs TdmaQos（实验组切片）
 * 2. LC调度器：LcRR（对照） vs LcQos（实验组）
 * 3. QoS Flow：uRLLC使用DGBR_INTER_SERV_87（高优先级），eMBB使用NGBR_LOW_LAT_EMBB（低优先级）
 */

int
main(int argc, char* argv[])
{
    // =====================================================================
    // 1. 参数定义与默认值
    // =====================================================================

    // 场景参数
    uint16_t gNbNum = 1;              // 小区数量
    uint16_t embbUeNum = 4;           // eMBB UE数量
    uint16_t urllcUeNum = 2;          // uRLLC UE数量
    bool logging = false;

    // 实验控制参数
    bool enableSlicing = true;        // 是否启用切片（实验组开关）
    std::string schedulerType = "Qos"; // 调度器类型: "RR", "PF", "Qos"
    bool enableLcQos = true;          // 是否启用QoS LC调度器
    bool enableMobility = false;   // 是否启用UE移动性（默认关闭，避免仿真过慢）
    bool enableShadow = false;     // 是否开启阴影衰落

    // 业务负载参数
    uint32_t urllcPacketSize = 100;   // uRLLC包大小 (bytes)
    uint32_t embbPacketSize = 1252;   // eMBB包大小 (bytes)
    double urllcLoadKbps = 200000.0;     // uRLLC负载 (kbps per UE)
    double embbLoadMbps = 5000.0;        // eMBB总负载 (Mbps)
    double ueSpeed = 1.0;          // UE移动速度，单位 m/s

    // 仿真时间参数
    Time simTime = MilliSeconds(1000);
    Time udpAppStartTime = MilliSeconds(400);

    // NR无线参数
    uint16_t numerology = 4;          // 子载波间隔: 4对应60kHz (28GHz频段常用)
    double centralFrequency = 28e9;   // 中心频率 28 GHz
    double bandwidth = 100e6;         // 带宽 100 MHz
    double totalTxPower = 35;         // 总发射功率 35 dBm

    // QoS参数 (实验组配置)
    double urllcGbrKbps = 400.0;      // uRLLC保证比特率 (kbps)
    double urllcMbrKbps = 800.0;      // uRLLC最大比特率 (kbps)
    uint8_t urllcPriority = 1;        // uRLLC优先级 (1-127, 数字越小优先级越高)
    uint8_t embbPriority = 20;        // eMBB优先级 (较低优先级)

    // 输出参数
    std::string simTag = "default";
    std::string outputDir = "./results/";

    // =====================================================================
    // 2. 命令行参数解析
    // =====================================================================
    CommandLine cmd(__FILE__);

    // 场景参数
    cmd.AddValue("gNbNum", "Number of gNBs", gNbNum);
    cmd.AddValue("embbUeNum", "Number of eMBB UEs", embbUeNum);
    cmd.AddValue("urllcUeNum", "Number of uRLLC UEs", urllcUeNum);
    cmd.AddValue("logging", "Enable logging", logging);

    // 实验控制
    cmd.AddValue("enableSlicing", "Enable network slicing (true=TreGroup, false=ConGroup)", enableSlicing);
    cmd.AddValue("schedulerType", "Scheduler type: RR, PF, or Qos", schedulerType);
    cmd.AddValue("enableLcQos", "Enable QoS LC scheduler (true=TreGroup, false=ConGroup)", enableLcQos);

    // 业务负载
    cmd.AddValue("urllcLoad", "uRLLC load per UE in kbps", urllcLoadKbps);
    cmd.AddValue("embbLoad", "Total eMBB load in Mbps", embbLoadMbps);
    cmd.AddValue("urllcPacketSize", "uRLLC packet size in bytes", urllcPacketSize);
    cmd.AddValue("embbPacketSize", "eMBB packet size in bytes", embbPacketSize);

    // 时间参数
    cmd.AddValue("simTime", "Simulation time in ms", simTime);
    cmd.AddValue("appStartTime", "Application start time in ms", udpAppStartTime);

    // 无线参数
    cmd.AddValue("numerology", "Numerology (0-4)", numerology);
    cmd.AddValue("frequency", "Center frequency in Hz", centralFrequency);
    cmd.AddValue("bandwidth", "System bandwidth in Hz", bandwidth);
    cmd.AddValue("txPower", "Total TX power in dBm", totalTxPower);
    cmd.AddValue("enableShadow", "Enable shadowing", enableShadow);

    // QoS参数
    cmd.AddValue("urllcGbr", "uRLLC GBR in kbps", urllcGbrKbps);
    cmd.AddValue("urllcMbr", "uRLLC MBR in kbps", urllcMbrKbps);
    cmd.AddValue("urllcPriority", "uRLLC priority (1-127)", urllcPriority);
    cmd.AddValue("embbPriority", "eMBB priority (1-127)", embbPriority);

    // 移动参数
    cmd.AddValue("enableMobility", "Enable random walk mobility for UEs", enableMobility);
    cmd.AddValue("ueSpeed", "UE speed in m/s (if mobility enabled)", ueSpeed);

    // 输出
    cmd.AddValue("simTag", "Tag for output files", simTag);
    cmd.AddValue("outputDir", "Output directory", outputDir);

    cmd.Parse(argc, argv);

    // =====================================================================
    // 3. 参数验证与计算
    // =====================================================================

    // 频率范围检查
    NS_ABORT_IF(centralFrequency < 0.5e9 || centralFrequency > 100e9);

    // 计算业务到达率 (packets per second)
    // uRLLC: 周期性小流量，高可靠性要求
    double urllcRateBps = urllcLoadKbps * 1000;  // per UE
    double urllcPps = urllcRateBps / (urllcPacketSize * 8.0);

    // eMBB: 突发大流量，尽力而为
    double embbTotalRateBps = embbLoadMbps * 1e6;
    double embbRatePerUeBps = embbTotalRateBps / embbUeNum;
    double embbPpsPerUe = embbRatePerUeBps / (embbPacketSize * 8.0);

    // 根据切片模式调整调度器配置
    std::string actualSchedulerType = schedulerType;
    if (!enableSlicing) {
        // 对照组：强制使用RR调度器，无视输入参数
        actualSchedulerType = "RR";
        enableLcQos = false;
    }

    // =====================================================================
    // 4. 日志配置
    // =====================================================================
    if (logging)
    {
        LogComponentEnable("UdpClient", LOG_LEVEL_INFO);
        LogComponentEnable("UdpServer", LOG_LEVEL_INFO);
        LogComponentEnable("NrMacSchedulerNs3", LOG_LEVEL_INFO);
        LogComponentEnable("NrMacSchedulerTdmaQos", LOG_LEVEL_INFO);
        LogComponentEnable("NrGnbMac", LOG_LEVEL_INFO);
        LogComponentEnable("NrUeMac", LOG_LEVEL_INFO);
    }

    // 增大RLC缓冲区，避免缓冲区溢出导致丢包
    Config::SetDefault("ns3::NrRlcUm::MaxTxBufferSize", UintegerValue(999999999));

    // =====================================================================
    // 5. 创建场景拓扑 (使用GridScenarioHelper)
    // =====================================================================
    int64_t randomStream = 1;

    GridScenarioHelper gridScenario;
    gridScenario.SetRows(1);
    gridScenario.SetColumns(gNbNum);
    gridScenario.SetHorizontalBsDistance(10.0);   // gNB间水平距离
    gridScenario.SetVerticalBsDistance(10.0);     // gNB间垂直距离
    gridScenario.SetBsHeight(10.0);               // gNB高度
    gridScenario.SetUtHeight(1.5);                  // UE高度
    gridScenario.SetSectorization(GridScenarioHelper::SINGLE);
    gridScenario.SetBsNumber(gNbNum);
    gridScenario.SetUtNumber(embbUeNum + urllcUeNum);
    gridScenario.SetScenarioHeight(3);              // UE分布范围
    gridScenario.SetScenarioLength(3);

    randomStream += gridScenario.AssignStreams(randomStream);
    gridScenario.CreateScenario();

    // 分离eMBB和uRLLC UE容器
    NodeContainer ueEmbbContainer;
    NodeContainer ueUrllcContainer;

    uint32_t totalUes = gridScenario.GetUserTerminals().GetN();
    for (uint32_t j = 0; j < totalUes; ++j)
    {
        Ptr<Node> ue = gridScenario.GetUserTerminals().Get(j);
        if (j < embbUeNum)
        {
            ueEmbbContainer.Add(ue);
        }
        else
        {
            ueUrllcContainer.Add(ue);
        }
    }

    NS_LOG_INFO("Created " << totalUes << " UEs (" << embbUeNum << " eMBB, "
        << urllcUeNum << " uRLLC) and " << gNbNum << " gNBs");

    std::cout << "\n========== Scenario Configuration ==========" << std::endl;
    std::cout << "Total UEs: " << totalUes << " (eMBB: " << embbUeNum
        << ", uRLLC: " << urllcUeNum << ")" << std::endl;
    std::cout << "gNBs: " << gNbNum << std::endl;

    // =====================================================================
    // 6. 配置NR模块 (NrHelper)
    // =====================================================================

    Ptr<NrPointToPointEpcHelper> nrEpcHelper = CreateObject<NrPointToPointEpcHelper>();
    Ptr<IdealBeamformingHelper> idealBeamformingHelper = CreateObject<IdealBeamformingHelper>();
    Ptr<NrHelper> nrHelper = CreateObject<NrHelper>();

    nrHelper->SetBeamformingHelper(idealBeamformingHelper);
    nrHelper->SetEpcHelper(nrEpcHelper);

    // 核心网延迟配置
    nrEpcHelper->SetAttribute("S1uLinkDelay", TimeValue(MilliSeconds(0)));

    // =====================================================================
    // 7. 调度器配置 (关键差异化配置)
    // =====================================================================

    std::stringstream schedulerName;
    schedulerName << "ns3::NrMacSchedulerTdma" << actualSchedulerType;

    std::cout << "\n========== Scheduler Configuration ==========" << std::endl;
    std::cout << "Slicing enabled: " << (enableSlicing ? "YES (TreGroup)" : "NO (ConGroup)") << std::endl;
    std::cout << "Scheduler: " << schedulerName.str() << std::endl;
    std::cout << "LC Scheduler: " << (enableLcQos ? "QoS (TreGroup)" : "RR (ConGroup)") << std::endl;

    TypeId schedulerTypeId = TypeId::LookupByName(schedulerName.str());
    nrHelper->SetSchedulerTypeId(schedulerTypeId);

    // LC调度器配置：实验组使用QoS感知，对照组使用RR
    if (enableLcQos && enableSlicing)
    {
        nrHelper->SetSchedulerAttribute("SchedLcAlgorithmType",
            TypeIdValue(NrMacSchedulerLcQos::GetTypeId()));
    }
    else
    {
        nrHelper->SetSchedulerAttribute("SchedLcAlgorithmType",
            TypeIdValue(NrMacSchedulerLcRR::GetTypeId()));
    }

    // =====================================================================
    // 8. 频谱配置 (单频段，单BWP)
    // =====================================================================

    BandwidthPartInfoPtrVector allBwps;
    CcBwpCreator ccBwpCreator;
    const uint8_t numCcPerBand = 1;

    // 创建操作频段配置
    CcBwpCreator::SimpleOperationBandConf bandConf(centralFrequency, bandwidth, numCcPerBand);
    OperationBandInfo band = ccBwpCreator.CreateOperationBandContiguousCc(bandConf);

    // 信道配置
    Ptr<NrChannelHelper> channelHelper = CreateObject<NrChannelHelper>();
    channelHelper->ConfigureFactories("UMi", "Default", "ThreeGpp");

    if(enableShadow == false)
    {
        // 无阴影衰落
        channelHelper->SetChannelConditionModelAttribute("UpdatePeriod", TimeValue(MilliSeconds(0)));
        channelHelper->SetPathlossAttribute("ShadowingEnabled", BooleanValue(false));
    }
    else
    {
        // 有阴影衰落
        channelHelper->SetChannelConditionModelAttribute("UpdatePeriod", TimeValue(MilliSeconds(100)));
        channelHelper->SetPathlossAttribute("ShadowingEnabled", BooleanValue(true));
    }
    
    channelHelper->AssignChannelsToBands({ band });

    allBwps = CcBwpCreator::GetAllBwps({ band });

    // =====================================================================
    // 9. 天线与物理层配置
    // =====================================================================

    // 波束成形方法
    idealBeamformingHelper->SetAttribute("BeamformingMethod",
        TypeIdValue(DirectPathBeamforming::GetTypeId()));

    // UE天线配置
    nrHelper->SetUeAntennaAttribute("NumRows", UintegerValue(2));
    nrHelper->SetUeAntennaAttribute("NumColumns", UintegerValue(4));
    nrHelper->SetUeAntennaAttribute("AntennaElement",
        PointerValue(CreateObject<IsotropicAntennaModel>()));

    // gNB天线配置
    nrHelper->SetGnbAntennaAttribute("NumRows", UintegerValue(4));
    nrHelper->SetGnbAntennaAttribute("NumColumns", UintegerValue(8));
    nrHelper->SetGnbAntennaAttribute("AntennaElement",
        PointerValue(CreateObject<IsotropicAntennaModel>()));

    // =====================================================================
    // 10. QoS Flow与BWP映射配置 (实验组关键配置)
    // =====================================================================

    if (enableSlicing)
    {
        std::cout << "\n========== QoS Flow Configuration (TreGroup) ==========" << std::endl;

        // uRLLC: 使用DGBR_INTER_SERV_87 (延迟关键GBR业务，最高优先级)
        // 5QI 87对应延迟关键GBR，用于uRLLC
        nrHelper->SetGnbBwpManagerAlgorithmAttribute("DGBR_INTER_SERV_87", UintegerValue(0));
        nrHelper->SetUeBwpManagerAlgorithmAttribute("DGBR_INTER_SERV_87", UintegerValue(0));

        // eMBB: 使用NGBR_LOW_LAT_EMBB (低延迟eMBB，较低优先级)
        // 注意：这里使用NGBR_LOW_LAT_EMBB而不是NGBR_VIDEO_TCP_DEFAULT
        nrHelper->SetGnbBwpManagerAlgorithmAttribute("NGBR_LOW_LAT_EMBB", UintegerValue(0));
        nrHelper->SetUeBwpManagerAlgorithmAttribute("NGBR_LOW_LAT_EMBB", UintegerValue(0));

        std::cout << "uRLLC Flow: DGBR_INTER_SERV_87 (5QI 87, Priority "
            << (int)urllcPriority << ")" << std::endl;
        std::cout << "eMBB Flow: NGBR_LOW_LAT_EMBB (5QI 80, Priority "
            << (int)embbPriority << ")" << std::endl;
        std::cout << "uRLLC GBR: " << urllcGbrKbps << " kbps, MBR: "
            << urllcMbrKbps << " kbps" << std::endl;
    }
    else
    {
        std::cout << "\n========== QoS Flow Configuration (ConGroup) ==========" << std::endl;
        std::cout << "All UEs use same QoS configuration (NGBR_LOW_LAT_EMBB)" << std::endl;

        // 对照组：所有业务使用相同配置
        nrHelper->SetGnbBwpManagerAlgorithmAttribute("NGBR_LOW_LAT_EMBB", UintegerValue(0));
        nrHelper->SetUeBwpManagerAlgorithmAttribute("NGBR_LOW_LAT_EMBB", UintegerValue(0));
    }

    // =====================================================================
    // 可选：为用户终端安装移动性模型
    // =====================================================================

    if (enableMobility)
    {
        MobilityHelper mobility;
        // 使用随机游走模型，边界与场景大小匹配
        mobility.SetPositionAllocator("ns3::RandomRectanglePositionAllocator",
            "X", StringValue("ns3::UniformRandomVariable[Min=0|Max=3]"),
            "Y", StringValue("ns3::UniformRandomVariable[Min=0|Max=3]"));
        mobility.SetMobilityModel("ns3::RandomWalk2dMobilityModel",
            "Bounds", RectangleValue(Rectangle(0, 3, 0, 3)),
            "Speed", StringValue("ns3::ConstantRandomVariable[Constant=" + std::to_string(ueSpeed) + "]"));
        mobility.Install(gridScenario.GetUserTerminals());

        std::cout << "UE mobility enabled, speed = " << ueSpeed << " m/s" << std::endl;
    }

    // =====================================================================
    // 11. 安装NR设备
    // =====================================================================

    NetDeviceContainer gnbNetDev =
        nrHelper->InstallGnbDevice(gridScenario.GetBaseStations(), allBwps);
    NetDeviceContainer ueEmbbNetDev =
        nrHelper->InstallUeDevice(ueEmbbContainer, allBwps);
    NetDeviceContainer ueUrllcNetDev =
        nrHelper->InstallUeDevice(ueUrllcContainer, allBwps);

    randomStream += nrHelper->AssignStreams(gnbNetDev, randomStream);
    randomStream += nrHelper->AssignStreams(ueEmbbNetDev, randomStream);
    randomStream += nrHelper->AssignStreams(ueUrllcNetDev, randomStream);

    // 配置物理层参数
    double x = pow(10, totalTxPower / 10);
    NrHelper::GetGnbPhy(gnbNetDev.Get(0), 0)
        ->SetAttribute("Numerology", UintegerValue(numerology));
    NrHelper::GetGnbPhy(gnbNetDev.Get(0), 0)
        ->SetAttribute("TxPower", DoubleValue(10 * log10(x)));

    // =====================================================================
    // 12. 网络层配置 (Internet + EPC)
    // =====================================================================

    auto [remoteHost, remoteHostIpv4Address] =
        nrEpcHelper->SetupRemoteHost("100Gb/s", 2500, Seconds(0.000));

    InternetStackHelper internet;
    internet.Install(gridScenario.GetUserTerminals());

    Ipv4InterfaceContainer ueEmbbIpIface =
        nrEpcHelper->AssignUeIpv4Address(NetDeviceContainer(ueEmbbNetDev));
    Ipv4InterfaceContainer ueUrllcIpIface =
        nrEpcHelper->AssignUeIpv4Address(NetDeviceContainer(ueUrllcNetDev));

    // UE附着到最近的gNB
    nrHelper->AttachToClosestGnb(ueEmbbNetDev, gnbNetDev);
    nrHelper->AttachToClosestGnb(ueUrllcNetDev, gnbNetDev);

    // =====================================================================
    // 13. 业务应用配置 (UDP流量生成器)
    // =====================================================================

    // 端口分配
    uint16_t dlPortUrllc = 1234;   // uRLLC业务端口
    uint16_t dlPortEmbb = 1235;    // eMBB业务端口

    // 服务器端 (UE侧接收)
    ApplicationContainer serverApps;
    UdpServerHelper dlPacketSinkUrllc(dlPortUrllc);
    UdpServerHelper dlPacketSinkEmbb(dlPortEmbb);

    serverApps.Add(dlPacketSinkUrllc.Install(ueUrllcContainer));
    serverApps.Add(dlPacketSinkEmbb.Install(ueEmbbContainer));

    // 客户端配置
    UdpClientHelper dlClientUrllc;
    dlClientUrllc.SetAttribute("MaxPackets", UintegerValue(0xFFFFFFFF));
    dlClientUrllc.SetAttribute("PacketSize", UintegerValue(urllcPacketSize));
    dlClientUrllc.SetAttribute("Interval", TimeValue(Seconds(1.0 / urllcPps)));

    UdpClientHelper dlClientEmbb;
    dlClientEmbb.SetAttribute("MaxPackets", UintegerValue(0xFFFFFFFF));
    dlClientEmbb.SetAttribute("PacketSize", UintegerValue(embbPacketSize));
    dlClientEmbb.SetAttribute("Interval", TimeValue(Seconds(1.0 / embbPpsPerUe)));

    std::cout << "\n========== Traffic Configuration ==========" << std::endl;
    std::cout << "uRLLC: " << urllcUeNum << " UEs, " << urllcLoadKbps
        << " kbps/UE, " << urllcPacketSize << " bytes/pkt, "
        << std::fixed << std::setprecision(1) << urllcPps << " pps" << std::endl;
    std::cout << "eMBB: " << embbUeNum << " UEs, " << embbLoadMbps
        << " Mbps total, " << embbPacketSize << " bytes/pkt, "
        << embbPpsPerUe << " pps/UE" << std::endl;

    // =====================================================================
    // 14. QoS Flow激活 (实验组关键差异化配置)
    // =====================================================================

    ApplicationContainer clientApps;

    // --- uRLLC业务配置 ---
    Ptr<NrQosRule> urllcRule = Create<NrQosRule>();
    NrQosRule::PacketFilter urllcFilter;
    urllcFilter.localPortStart = dlPortUrllc;
    urllcFilter.localPortEnd = dlPortUrllc;
    urllcRule->Add(urllcFilter);

    NrQosFlow urllcFlow;
    if (enableSlicing)
    {
        // 实验组：uRLLC使用GBR配置，确保低延迟
        NrGbrQosInformation gbrInfo;
        gbrInfo.gbrDl = urllcGbrKbps * 1000;  // bps
        gbrInfo.mbrDl = urllcMbrKbps * 1000;  // bps
        urllcFlow = NrQosFlow(NrQosFlow::DGBR_INTER_SERV_87, gbrInfo);
    }
    else
    {
        // 对照组：使用NGBR配置
        urllcFlow = NrQosFlow(NrQosFlow::NGBR_VIDEO_TCP_DEFAULT);
    }

    // 安装uRLLC客户端并激活QoS Flow
    for (uint32_t i = 0; i < ueUrllcContainer.GetN(); ++i)
    {
        Ptr<Node> ue = ueUrllcContainer.Get(i);
        Ptr<NetDevice> ueDevice = ueUrllcNetDev.Get(i);
        Address ueAddress = ueUrllcIpIface.GetAddress(i);

        dlClientUrllc.SetAttribute("Remote",
            AddressValue(addressUtils::ConvertToSocketAddress(ueAddress, dlPortUrllc)));
        clientApps.Add(dlClientUrllc.Install(remoteHost));

        // 激活专用QoS Flow
        nrHelper->ActivateDedicatedQosFlow(ueDevice, urllcFlow, urllcRule);
    }

    // --- eMBB业务配置 ---
    Ptr<NrQosRule> embbRule = Create<NrQosRule>();
    NrQosRule::PacketFilter embbFilter;
    embbFilter.localPortStart = dlPortEmbb;
    embbFilter.localPortEnd = dlPortEmbb;
    embbRule->Add(embbFilter);

    NrQosFlow embbFlow;
    if (enableSlicing)
    {
        // 实验组：eMBB使用NGBR配置，尽力而为
        // 使用NGBR_VIDEO_TCP_DEFAULT (5QI 20) 作为eMBB的低优先级配置
        embbFlow = NrQosFlow(NrQosFlow::NGBR_VIDEO_TCP_DEFAULT);
    }
    else
    {
        // 对照组：同样使用NGBR配置
        embbFlow = NrQosFlow(NrQosFlow::NGBR_LOW_LAT_EMBB);
    }

    // 安装eMBB客户端并激活QoS Flow
    for (uint32_t i = 0; i < ueEmbbContainer.GetN(); ++i)
    {
        Ptr<Node> ue = ueEmbbContainer.Get(i);
        Ptr<NetDevice> ueDevice = ueEmbbNetDev.Get(i);
        Address ueAddress = ueEmbbIpIface.GetAddress(i);

        dlClientEmbb.SetAttribute("Remote",
            AddressValue(addressUtils::ConvertToSocketAddress(ueAddress, dlPortEmbb)));
        clientApps.Add(dlClientEmbb.Install(remoteHost));

        // 激活专用QoS Flow
        nrHelper->ActivateDedicatedQosFlow(ueDevice, embbFlow, embbRule);
    }

    // 启动应用
    serverApps.Start(udpAppStartTime);
    clientApps.Start(udpAppStartTime);
    serverApps.Stop(simTime);
    clientApps.Stop(simTime);

    // =====================================================================
    // 15. FlowMonitor性能监测配置
    // =====================================================================

    FlowMonitorHelper flowmonHelper;
    NodeContainer endpointNodes;
    endpointNodes.Add(remoteHost);
    endpointNodes.Add(gridScenario.GetUserTerminals());

    Ptr<FlowMonitor> monitor = flowmonHelper.Install(endpointNodes);
    monitor->SetAttribute("DelayBinWidth", DoubleValue(0.001));
    monitor->SetAttribute("JitterBinWidth", DoubleValue(0.001));
    monitor->SetAttribute("PacketSizeBinWidth", DoubleValue(20));

    // =====================================================================
    // 16. 运行仿真
    // =====================================================================

    std::cout << "\n========== Starting Simulation ==========" << std::endl;
    std::cout << "Simulation time: " << simTime.GetMilliSeconds() << " ms" << std::endl;
    std::cout << "Application duration: " << (simTime - udpAppStartTime).GetMilliSeconds()
        << " ms" << std::endl;

    Simulator::Stop(simTime);
    Simulator::Run();

    // =====================================================================
    // 17. 结果统计与分析（分离人类可读和机器可读输出）
    // =====================================================================

    std::cout << "\n========== Simulation Results ==========" << std::endl;

    // 创建输出目录
    std::string mkdirCmd = "mkdir -p " + outputDir;
    int mkdirRet = system(mkdirCmd.c_str());
    if (mkdirRet != 0) {
        std::cerr << "Warning: Failed to create directory " << outputDir << std::endl;
    }

    // 生成输出文件名基础
    std::ostringstream filename;
    filename << outputDir << simTag << "_"
        << (enableSlicing ? "slic" : "nosli") << "_"
        << actualSchedulerType << "_"
        << "u" << urllcUeNum << "_e" << embbUeNum ;
    std::string baseName = filename.str();

    std::string statsFile = baseName + "_stats.txt";   // 人类可读
    std::string reportFile = baseName + "_report.csv"; // 机器可读
    std::string flowmonFile = baseName + "_flowmonitor.xml";

    // 保存FlowMonitor原始数据
    monitor->SerializeToXmlFile(flowmonFile, true, true);
    std::cout << "FlowMonitor data saved to: " << flowmonFile << std::endl;

    // 处理统计数据
    monitor->CheckForLostPackets();
    Ptr<Ipv4FlowClassifier> classifier =
        DynamicCast<Ipv4FlowClassifier>(flowmonHelper.GetClassifier());
    FlowMonitor::FlowStatsContainer stats = monitor->GetFlowStats();

    // 打开两个输出文件
    std::ofstream humanFile;   // _stats.txt
    std::ofstream machineFile; // _report.csv

    humanFile.open(statsFile.c_str(), std::ofstream::out | std::ofstream::trunc);
    machineFile.open(reportFile.c_str(), std::ofstream::out | std::ofstream::trunc);

    if (!humanFile.is_open())
    {
        std::cerr << "Error: Cannot open file " << statsFile << std::endl;
        return 1;
    }
    if (!machineFile.is_open())
    {
        std::cerr << "Error: Cannot open file " << reportFile << std::endl;
        return 1;
    }

    humanFile.setf(std::ios_base::fixed);
    machineFile.setf(std::ios_base::fixed);

    // ========== 人类可读文件：写入实验配置和元数据 ==========
    humanFile << "========== Experiment Configuration ==========\n";
    humanFile << "Slicing Enabled: " << (enableSlicing ? "Yes" : "No") << "\n";
    humanFile << "Scheduler Type: " << actualSchedulerType << "\n";
    humanFile << "LC Scheduler: " << (enableLcQos ? "QoS" : "RR") << "\n";
    humanFile << "uRLLC UEs: " << urllcUeNum << ", Load: " << urllcLoadKbps << " kbps/UE\n";
    humanFile << "eMBB UEs: " << embbUeNum << ", Load: " << embbLoadMbps << " Mbps total\n";
    humanFile << "Simulation Time: " << simTime.GetMilliSeconds() << " ms\n";
    humanFile << "Application Duration: " << (simTime - udpAppStartTime).GetMilliSeconds() << " ms\n";
    humanFile << "===========================================\n\n";

    // 添加时间戳
    auto now = std::chrono::system_clock::now();
    std::time_t now_time = std::chrono::system_clock::to_time_t(now);
    humanFile << "Simulation timestamp: " << std::put_time(std::localtime(&now_time), "%Y-%m-%d %H:%M:%S") << "\n\n";

    // ========== 机器可读文件：写入CSV头部 ==========
    // 元数据行（以#开头，便于人类阅读，机器可忽略）
    machineFile << "# TIMESTAMP," << std::put_time(std::localtime(&now_time), "%Y-%m-%d %H:%M:%S") << "\n";
    machineFile << "# SIMULATION_CONFIG,simTag,slicingEnabled,schedulerType,lcQosEnabled,urllcUeNum,embbUeNum,urllcLoadKbps,embbLoadMbps,urllcPriority,embbPriority,flowDurationSec,gNbNum,enableShadow,enableMobility,ueSpeed\n";
    machineFile << "# CONFIG," << simTag << ","
        << (enableSlicing ? "1" : "0") << ","
        << actualSchedulerType << ","
        << (enableLcQos ? "1" : "0") << ","
        << urllcUeNum << ","
        << embbUeNum << ","
        << urllcLoadKbps << ","
        << embbLoadMbps << ","
        << static_cast<int>(urllcPriority) << ","
        << static_cast<int>(embbPriority) << ","
        << (simTime - udpAppStartTime).GetSeconds() << ","
        << gNbNum << ","
        << (enableShadow ? "1" : "0") << ","
        << (enableMobility ? "1" : "0") << ","
        << ueSpeed << "\n";
    machineFile << "# COLUMN_HEADERS: TYPE,FlowID,FlowType,SrcIP,DstIP,DstPort,TxPackets,RxPackets,LostPackets,LossRate%,ThroughputMbps,DelayMs,JitterMs,DelaySumSec,JitterSumSec,RxBytes\n";

    // 统计变量
    double flowDuration = (simTime - udpAppStartTime).GetSeconds();

    struct FlowMetrics {
        double totalThroughput = 0.0;
        double totalDelay = 0.0;
        double totalJitter = 0.0;
        uint64_t txPackets = 0;
        uint64_t rxPackets = 0;
        uint64_t lostPackets = 0;
        uint32_t flowCount = 0;
        std::vector<double> delaySamples;  // 用于计算百分位数
        double minDelay = 999999.0;
        double maxDelay = 0.0;

        void UpdateDelayStats(double delay) {
            if (delay > 0) {
                delaySamples.push_back(delay);
                if (delay < minDelay) minDelay = delay;
                if (delay > maxDelay) maxDelay = delay;
            }
        }
    };

    FlowMetrics urllcMetrics, embbMetrics, overallMetrics;

    // ========== 处理每个Flow：写入机器可读的 FLOW_DETAIL 行 ==========
    for (auto it = stats.begin(); it != stats.end(); ++it)
    {
        Ipv4FlowClassifier::FiveTuple t = classifier->FindFlow(it->first);

        bool isUrllc = (t.destinationPort == dlPortUrllc);
        bool isEmbb = (t.destinationPort == dlPortEmbb);
        std::string flowType = isUrllc ? "uRLLC" : (isEmbb ? "eMBB" : "Other");

        double throughput = 0.0;
        double delay = 0.0;
        double jitter = 0.0;
        uint64_t lost = it->second.txPackets - it->second.rxPackets;
        double lossRate = (it->second.txPackets > 0) ?
            (100.0 * lost / it->second.txPackets) : 0.0;

        if (it->second.rxPackets > 0)
        {
            throughput = it->second.rxBytes * 8.0 / flowDuration / 1e6;  // Mbps
            delay = 1000.0 * it->second.delaySum.GetSeconds() / it->second.rxPackets;  // ms
            jitter = 1000.0 * it->second.jitterSum.GetSeconds() / it->second.rxPackets;  // ms
        }

        // 写入机器可读文件 (CSV格式)
        machineFile << "FLOW_DETAIL,"
            << it->first << ","
            << flowType << ","
            << t.sourceAddress << ","
            << t.destinationAddress << ","
            << t.destinationPort << ","
            << it->second.txPackets << ","
            << it->second.rxPackets << ","
            << lost << ","
            << std::setprecision(4) << lossRate << ","
            << std::setprecision(6) << throughput << ","
            << std::setprecision(6) << delay << ","
            << std::setprecision(6) << jitter << ","
            << it->second.delaySum.GetSeconds() << ","
            << it->second.jitterSum.GetSeconds() << ","
            << it->second.rxBytes << "\n";

        // 累加统计
        if (isUrllc)
        {
            urllcMetrics.totalThroughput += throughput;
            urllcMetrics.totalDelay += delay;
            urllcMetrics.totalJitter += jitter;
            urllcMetrics.txPackets += it->second.txPackets;
            urllcMetrics.rxPackets += it->second.rxPackets;
            urllcMetrics.lostPackets += lost;
            if (it->second.rxPackets > 0) {
                urllcMetrics.flowCount++;
                urllcMetrics.UpdateDelayStats(delay);
            }
        }
        else if (isEmbb)
        {
            embbMetrics.totalThroughput += throughput;
            embbMetrics.totalDelay += delay;
            embbMetrics.totalJitter += jitter;
            embbMetrics.txPackets += it->second.txPackets;
            embbMetrics.rxPackets += it->second.rxPackets;
            embbMetrics.lostPackets += lost;
            if (it->second.rxPackets > 0) {
                embbMetrics.flowCount++;
                embbMetrics.UpdateDelayStats(delay);
            }
        }
    }

    // ========== 输出机器可读的 SUMMARY 行到 _report.csv ==========
    auto writeMachineSummary = [&](std::ofstream& out, const std::string& name, FlowMetrics& m, uint32_t expectedFlows) {
        double p95Delay = 0.0, p99Delay = 0.0;
        double effectiveMinDelay = 0.0, effectiveMaxDelay = 0.0;
        if (!m.delaySamples.empty()) {
            std::vector<double> sortedDelays = m.delaySamples;
            std::sort(sortedDelays.begin(), sortedDelays.end());
            size_t p95Idx = static_cast<size_t>(sortedDelays.size() * 0.95);
            size_t p99Idx = static_cast<size_t>(sortedDelays.size() * 0.99);
            if (p95Idx >= sortedDelays.size()) p95Idx = sortedDelays.size() - 1;
            if (p99Idx >= sortedDelays.size()) p99Idx = sortedDelays.size() - 1;
            p95Delay = sortedDelays[p95Idx];
            p99Delay = sortedDelays[p99Idx];
            effectiveMinDelay = sortedDelays.front();
            effectiveMaxDelay = sortedDelays.back();
        }
        double avgDelay = (m.flowCount > 0) ? m.totalDelay / m.flowCount : 0.0;
        double avgJitter = (m.flowCount > 0) ? m.totalJitter / m.flowCount : 0.0;
        double avgThroughput = (m.flowCount > 0) ? m.totalThroughput / m.flowCount : 0.0;
        double lossRate = (m.txPackets > 0) ? 100.0 * m.lostPackets / m.txPackets : 0.0;

        out << "SUMMARY,"
            << name << ","
            << m.flowCount << ","
            << expectedFlows << ","
            << std::setprecision(6) << m.totalThroughput << ","
            << std::setprecision(6) << avgThroughput << ","
            << std::setprecision(6) << avgDelay << ","
            << std::setprecision(6) << effectiveMinDelay << ","
            << std::setprecision(6) << effectiveMaxDelay << ","
            << std::setprecision(6) << p95Delay << ","
            << std::setprecision(6) << p99Delay << ","
            << std::setprecision(6) << avgJitter << ","
            << m.txPackets << ","
            << m.rxPackets << ","
            << m.lostPackets << ","
            << std::setprecision(4) << lossRate << "\n";
        };

    // 写入机器可读的 SUMMARY 行
    writeMachineSummary(machineFile, "uRLLC", urllcMetrics, urllcUeNum);
    writeMachineSummary(machineFile, "eMBB", embbMetrics, embbUeNum);

    // ========== 输出人类可读的摘要到 _stats.txt ==========
    auto writeHumanSummary = [&](std::ofstream& out, const std::string& name, FlowMetrics& m, uint32_t expectedFlows) {
        double p95Delay = 0.0, p99Delay = 0.0;
        double effectiveMinDelay = 0.0, effectiveMaxDelay = 0.0;
        if (!m.delaySamples.empty()) {
            std::vector<double> sortedDelays = m.delaySamples;
            std::sort(sortedDelays.begin(), sortedDelays.end());
            size_t p95Idx = static_cast<size_t>(sortedDelays.size() * 0.95);
            size_t p99Idx = static_cast<size_t>(sortedDelays.size() * 0.99);
            if (p95Idx >= sortedDelays.size()) p95Idx = sortedDelays.size() - 1;
            if (p99Idx >= sortedDelays.size()) p99Idx = sortedDelays.size() - 1;
            p95Delay = sortedDelays[p95Idx];
            p99Delay = sortedDelays[p99Idx];
            effectiveMinDelay = sortedDelays.front();
            effectiveMaxDelay = sortedDelays.back();
        }
        double avgDelay = (m.flowCount > 0) ? m.totalDelay / m.flowCount : 0.0;
        double avgJitter = (m.flowCount > 0) ? m.totalJitter / m.flowCount : 0.0;
        double avgThroughput = (m.flowCount > 0) ? m.totalThroughput / m.flowCount : 0.0;
        double lossRate = (m.txPackets > 0) ? 100.0 * m.lostPackets / m.txPackets : 0.0;

        out << "---------- " << name << " Summary ----------\n";
        out << "Active Flows: " << m.flowCount << "/" << expectedFlows << "\n";
        out << "Total Throughput: " << std::setprecision(3) << m.totalThroughput << " Mbps\n";
        out << "Avg Throughput/Flow: " << avgThroughput << " Mbps\n";
        out << "Avg Delay: " << avgDelay << " ms\n";
        out << "Min/Max Delay: " << effectiveMinDelay << " / " << effectiveMaxDelay << " ms\n";
        out << "P95/P99 Delay: " << p95Delay << " / " << p99Delay << " ms\n";
        out << "Avg Jitter: " << avgJitter << " ms\n";
        out << "Total Tx/Rx/Lost: " << m.txPackets << "/" << m.rxPackets << "/" << m.lostPackets << "\n";
        out << "Loss Rate: " << lossRate << "%\n\n";

        // 同时输出到控制台
        std::cout << "\n" << name << " Results:" << std::endl;
        std::cout << "  Throughput: " << m.totalThroughput << " Mbps (total), "
            << avgThroughput << " Mbps/flow avg" << std::endl;
        std::cout << "  Delay: " << avgDelay << " ms avg, P95: " << p95Delay << " ms" << std::endl;
        std::cout << "  Loss Rate: " << lossRate << "%" << std::endl;
        };

    // 写入人类可读摘要
    writeHumanSummary(humanFile, "uRLLC", urllcMetrics, urllcUeNum);
    writeHumanSummary(humanFile, "eMBB", embbMetrics, embbUeNum);

    humanFile << "========== End of Human-Readable Report ==========\n";
    machineFile << "# End of Machine-Readable Report\n";

    humanFile.close();
    machineFile.close();

    std::cout << "\nHuman-readable statistics saved to: " << statsFile << std::endl;
    std::cout << "Machine-readable statistics saved to: " << reportFile << std::endl;
    std::cout << "========================================\n" << std::endl;

    Simulator::Destroy();
    return 0;
}