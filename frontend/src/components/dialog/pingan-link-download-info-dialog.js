import React, { Fragment, Component } from 'react';
import PropTypes from 'prop-types';
import { Button, Modal, ModalHeader, ModalBody, ModalFooter } from 'reactstrap';
import { gettext, isSystemSecurity, isCompanySecurity } from '../../utils/constants';
import EmptyTip from '../../components/empty-tip';
import Loading from '../../components/loading';
import { seafileAPI } from '../../utils/seafile-api';
import { Utils } from '../../utils/utils';
import toaster from '../../components/toast';
import moment from 'moment';

class Content extends Component {

  constructor(props) {
    super(props);
  }

  render() {
    const { loading, errorMsg, items } = this.props;
    if (loading) {
      return <Loading />;
    } else if (errorMsg) {
      return <p className="error text-center">{errorMsg}</p>;
    } else {
      const emptyTip = (
        <EmptyTip>
          <h2>{gettext('没有外链下载信息')}</h2>
        </EmptyTip>
      );
      const table = (
        <Fragment>
          <table className="table-hover">
            <thead>
              <tr>
                <th width="15%">{'用户'}</th>
                <th width="20%">{'时间'}</th>
                <th width="12%">{'IP'}</th>
                <th width="53%">{'设备名'}</th>
              </tr>
            </thead>
            <tbody>
              {items && items.map((item, index) => {
                return (<Item
                  key={index}
                  item={item}
                />);
              })}
            </tbody>
          </table>
        </Fragment>
      );
      return items.length ? table : emptyTip; 
    }
  }
}

class Item extends Component {

  constructor(props) {
    super(props);
    this.state = {
      isOpIconShown: false,
    };
  }

  handleMouseEnter = () => {
    this.setState({isOpIconShown: true});
  }

  handleMouseLeave = () => {
    this.setState({isOpIconShown: false});
  }

  render() {
    let { item } = this.props;

    return (
      <Fragment>
        <tr onMouseEnter={this.handleMouseEnter} onMouseLeave={this.handleMouseLeave}>
          <td>{item.user}</td>
          <td>{moment(item.time).format('YYYY-MM-DD HH:mm:ss')}</td>
          <td>{item.ip}</td>
          <td>{item.device}</td>
        </tr>
      </Fragment>
    );
  }
}

const propTypes = {
  toggle: PropTypes.func.isRequired,
};

class PinganLinkDownloadInfoDialog extends React.Component {

  constructor(props) {
    super(props);
    this.state = {
      errorMsg: '',
      loading: true,
      infoList: [],
      firstDoawloadTime: null,
      downloadCnt: 0,
    };
  }

  componentDidMount() {
    this.listPinganShareLinkDownloadInfo().then(res => {
      this.setState({
        firstDoawloadTime: res.data[0].first_download_time,
        downloadCnt: res.data[0].download_count,
        infoList: res.data[0].data,
        loading: false,
      });
    }).catch(error => {
      let errMessage = Utils.getErrorMsg(error);
      toaster.danger(errMessage);
    });
  }

  listPinganShareLinkDownloadInfo = (start, end) => {
    let url = seafileAPI.server;
    if (isCompanySecurity) {
      url += '/pingan-api/company-security/share-link-download-info/';
    } else if (isSystemSecurity) {
      url += '/pingan-api/admin/share-link-download-info/';
    }
    return seafileAPI.req.get(url + '?share_link_token=' + this.props.shareLinkToken);
  }

  render() {
    let { errorMsg, loading, firstDoawloadTime, downloadCnt, infoList } = this.state;
    return (
      <Modal size="lg" isOpen={true} toggle={this.props.toggle}>
        <ModalHeader toggle={this.props.toggle}>{gettext('链接下载信息')}
        </ModalHeader>
        <div>
          <p className="ml-3 mb-0 mt-2">
            <span className="ml-1 mr-4">{'首次下载时间：'}{firstDoawloadTime ?
              moment(firstDoawloadTime).format('YYYY-MM-DD HH:mm:ss') : '--'}</span><br/>
            <span className="ml-1">{'下载次数：'}{downloadCnt}</span>
          </p>
        </div>
        <ModalBody>
          <Content
            loading={loading}
            errorMsg={errorMsg}
            items={infoList}
          />
        </ModalBody>
        <ModalFooter>
          <Button color="secondary" onClick={this.props.toggle}>{gettext('Close')}</Button>
        </ModalFooter>
      </Modal>
    );
  }
}

PinganLinkDownloadInfoDialog.propTypes = propTypes;

export default PinganLinkDownloadInfoDialog;
